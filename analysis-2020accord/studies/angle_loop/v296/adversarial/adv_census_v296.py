"""ADV build-audit V296 -- filesystem census + original-artifact integrity. Read-only; writes nothing.
No imports from any builder script. Exit code 0 = census ran (the VERDICT is in the printout)."""
import hashlib, pathlib, re, sys

PROJ = pathlib.Path(r"C:/Users/dudei/Desktop/Projects")
KIT, FW = PROJ / "accord-eps-torque-mod", PROJ / "accord-firmwares"
RECORD = {  # recorded sha256 (docs/BUILD-LINEAGE-PART6-V291-ONWARD.md, STATE.md, handoffs)
    "_v295_*_plain_image.bin": "5c044d65763140525a2c3651ded72e1e2111cd81ca8b41334366605fb40452ed",
    "39990-TVA,A160-V295-*.rwd": "f42a06bda5a737eb9f678d617603745ec21fb93c4bd229344f33259cfbeaae87",
    "_v294_*_plain_image.bin": "3143616d5b79bdb7648d8e4d32e48420c7b481b18325178e89d1853589dbdd85",
    "39990-TVA,A160-V294-*.rwd": "a2b418f061160f66ffaa8ac541a478d43771fcbd004a92dc3d7a071cfd9f706a",
}
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

# 1. any V296-named artifact anywhere in either repo (excluding .git and this audit folder)
own = KIT / "analysis-2020accord/studies/angle_loop/v296"
hits = [p for root in (KIT, FW) for p in root.rglob("*")
        if ".git" not in p.parts and re.search(r"v296|A16A|REHEADER", p.name, re.I)
        and own not in p.parents and p != own]
print(f"[F0/F1] V296 / A16A / REHEADERED artifacts found: {len(hits)}")
for p in hits: print("   ", p)
print(f"[F0] build_v296_tva.py exists: {(KIT/'analysis-2020accord/builds/v108_plus/build_v296_tva.py').exists()}")
rwd_dir, img_dir = FW / "flashing-2020accord/rwd", FW / "analysis-2020accord"
print(f"[F7] flashable .rwd carrying V296: {len([p for p in rwd_dir.glob('*V296*.rwd') if not p.name.startswith('SUPERSEDED')])}")

# 2. originals untouched
bad = 0
for pat, want in RECORD.items():
    d = rwd_dir if pat.endswith(".rwd") else img_dir
    fs = [p for p in d.glob(pat) if not p.name.startswith("SUPERSEDED")]
    for p in fs:
        got = sha(p); ok = got == want; bad += (not ok)
        print(f"[F8] {'OK  ' if ok else 'FAIL'} {got[:16]} {p.name[:60]}")
    if len(fs) != 1: bad += 1; print(f"[F8] FAIL expected exactly 1 file for {pat}, found {len(fs)}")

no_artifact = not hits
print("VERDICT:", "DO_NOT_FLASH (F0: no V296 artifact exists -- nothing has passed any gate)"
      if no_artifact else "DO_NOT_FLASH (F1: V296-named artifact(s) present but builder reported none)")
print("ORIGINALS:", "INTACT" if bad == 0 else f"{bad} PROBLEM(S)")
