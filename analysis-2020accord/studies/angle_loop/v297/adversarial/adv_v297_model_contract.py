"""ADV V297 -- re-run the golden-model verification contract (read-only; edits nothing).

Contract (kit CLAUDE.md, "VERIFICATION CONTRACT"): `import eps_lkas_chain_model` exposes exactly 94
NON-DUNDER symbols, and `_self_check()` + `_demo()` stdout sha256 ==
740f4bcd0534212a0c200a9359b0b4318e1419bea33823d66e2e89c12961102d (2,512 bytes).
Also: does a `_self_check_v297` exist anywhere in the model modules (the builder said none was written)?
"""
import contextlib, hashlib, io, os, re, sys

MODEL = r"C:\Users\dudei\Desktop\Projects\accord-eps-torque-mod\analysis-2020accord\model"
sys.path.insert(0, MODEL)
import eps_lkas_chain_model as M  # noqa: E402

names = [x for x in dir(M) if not x.startswith("__")]
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    M._self_check()
    M._demo()
out = buf.getvalue().encode("utf-8")
h = hashlib.sha256(out).hexdigest()
print(f"non-dunder symbols: {len(names)}  (expect 94)")
print(f"_self_check+_demo stdout: {len(out)} bytes  sha256 {h}")
print(f"expect                     2512 bytes  sha256 740f4bcd0534212a0c200a9359b0b4318e1419bea33823d66e2e89c12961102d")
ok = len(names) == 94 and h == "740f4bcd0534212a0c200a9359b0b4318e1419bea33823d66e2e89c12961102d"
hits = []
for f in os.listdir(MODEL):
    if f.endswith(".py"):
        for i, line in enumerate(open(os.path.join(MODEL, f), encoding="utf-8"), 1):
            if re.search(r"_self_check_v29[6-9]|V29[6-9]", line):
                hits.append(f"{f}:{i}: {line.strip()[:100]}")
print("V296..V299 mentions in model modules:", hits or "none")
print("CONTRACT", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
