"""ADV ARITHMETIC V297 -- presence / identity gate (criteria A0, A1, A11 in 00_FAIL_CRITERIA_written_first.txt).

Runs BEFORE any arithmetic re-derivation: an arithmetic pass needs the built image's bytes. If no V297
image exists, every arithmetic criterion A2-A10 is UNRUN, and the verdict is DO_NOT_FLASH (A0 + A11).

Also hashes (decoded bytes) the candidate C3-rev2 cave hex files and diffs flight vs score for each
pair. Those are NOT V297 and nothing below is a verdict on V297; they are recorded so the pass that
runs on a real image later can confirm which cave it is looking at.

Python: bin_decompile env (`python`). No imports from builder scripts.
"""
import hashlib
import os
import re
import sys
from pathlib import Path

FW = Path(os.environ.get("ACCORD_FIRMWARE_ROOT",
                         r"C:/Users/dudei/Desktop/Projects/accord-firmwares"))
KIT = Path(__file__).resolve().parents[5]          # .../accord-eps-torque-mod
REV2B = KIT / "analysis-2020accord/studies/angle_loop/c3/rev2B"

V295_IMG_SHA = "5c044d65763140525a2c3651ded72e1e2111cd81ca8b41334366605fb40452ed"
V295_RWD_SHA = "f42a06bda5a737eb9f678d617603745ec21fb93c4bd229344f33259cfbeaae87"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def hexfile_bytes(p: Path) -> bytes:
    txt = p.read_text()
    txt = "\n".join(line.split("#", 1)[0] for line in txt.splitlines())
    return bytes.fromhex(re.sub(r"\s+", "", txt))


def main() -> int:
    out = []
    pat = re.compile(r"v297", re.I)

    # A0 / A1: any V297-named artefact anywhere in the two repos (outside .git and this folder)?
    hits = []
    for root in (KIT, FW):
        for dp, dn, fn in os.walk(root):
            dn[:] = [d for d in dn if d != ".git"]
            for name in fn + dn:
                if pat.search(name):
                    full = Path(dp) / name
                    if "adversarial" in full.parts and "v297" in full.parts:
                        continue          # this pass's own files
                    hits.append(str(full))
    # also the studies/angle_loop/v297 folder itself (only adversarial/ allowed)
    v297dir = KIT / "analysis-2020accord/studies/angle_loop/v297"
    extra = [str(p) for p in v297dir.iterdir() if p.name != "adversarial"] if v297dir.exists() else []
    out.append(f"A0/A1 V297-named artefacts outside this pass: {hits + extra if hits + extra else 'NONE'}")

    imgs = sorted((FW / "analysis-2020accord").glob("_v297*_plain_image.bin"))
    rwds = sorted((FW / "flashing-2020accord/rwd").glob("*V297*.rwd"))
    script = KIT / "analysis-2020accord/builds/v108_plus/build_v297_tva.py"
    out.append(f"A0 plain image _v297*: {[p.name for p in imgs] or 'NONE'}")
    out.append(f"A0 .rwd *V297*:       {[p.name for p in rwds] or 'NONE'}")
    out.append(f"A0 build_v297_tva.py exists: {script.exists()}")

    # base / revert path intact (context for A2 when an image appears)
    v295_img = next((FW / "analysis-2020accord").glob("_v295_*_plain_image.bin"))
    v295_rwd = next((FW / "flashing-2020accord/rwd").glob("*-V295-*.rwd"))
    out.append(f"V295 image sha == recorded 5c044d65...: {sha(v295_img) == V295_IMG_SHA}")
    out.append(f"V295 .rwd  sha == recorded f42a06bd...: {sha(v295_rwd) == V295_RWD_SHA}")

    # candidate caves (NOT V297): decoded-byte hashes, flight vs score
    for tag in ("C3B-F", "C3B-P"):
        fl = REV2B / f"c3b_cave_{tag}.hex"
        sc = REV2B / f"c3b_cave_{tag}_score.hex"
        if not (fl.exists() and sc.exists()):
            out.append(f"{tag}: hex pair missing")
            continue
        bf, bs = hexfile_bytes(fl), hexfile_bytes(sc)
        diffs = [i for i in range(min(len(bf), len(bs))) if bf[i] != bs[i]]
        out.append(
            f"{tag}: flight {len(bf)} B sha {hashlib.sha256(bf).hexdigest()[:12]} | "
            f"score {len(bs)} B sha {hashlib.sha256(bs).hexdigest()[:12]} | "
            f"identical={bf == bs} | first diff offset="
            f"{hex(diffs[0]) if diffs else ('len-only' if len(bf) != len(bs) else 'none')} | "
            f"n_diff_bytes_in_common_prefix={len(diffs)}")

    verdict = "DO_NOT_FLASH" if not imgs else "IMAGE PRESENT -- run A2..A10"
    out.append(f"PRESENCE-GATE RESULT: {verdict}")
    print("\n".join(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
