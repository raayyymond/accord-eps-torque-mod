# -*- coding: utf-8 -*-
"""ARM-D: rev 6.4 exactly as flown on 6c/6d, with the disturbance observer OFF (AccordDobHz 0.6 -> 0.0).

Why (v282-reference REPORT.md): torque mode's clearest difference from V282 is 2.5-3 Hz wheel shake (x2.6-3.1 on rev 6.4
in matched speed x angle cells; x1 on the same EPS with an older fork). At the measured 30 ms command->wheel latency the
logged observer torque INJECTS energy into that band (b_eq -2.3..-3.9e-4, 4 routes, both speed bins) -- about as much as
the rest of the command damps at >=15 m/s. AccordDobHz <= 0 makes HondaAccordDisturbanceObserver.update return 0.

Exactly ONE setting differs from the as-flown config (asserted). Codec positive control runs first.
"""
import base64, json, os
from pathlib import Path

KIT = Path(__file__).resolve().parents[3]
REF = KIT / "analysis-2020accord" / "reference"
XOR_KEY = "s8#pL3*Xj!aZ@dWq"
FORMAT, VERSION = "starpilot-toggle-backup", 1


def xor(d, k):
    return "".join(chr(ord(c) ^ ord(k[i % len(k)])) for i, c in enumerate(d))


def enc(d):
    return base64.b64encode(xor(json.dumps(d), XOR_KEY).encode()).decode()


def dec(e):
    return json.loads(xor(base64.b64decode(e.encode()).decode(), XOR_KEY))


pairs = 0
for f in sorted(os.listdir(REF)):
    if not f.endswith(".decoded.json"):
        continue
    ep = REF / f.replace(".decoded.json", ".json")
    if not ep.exists():
        continue
    e = json.load(open(ep, encoding="utf-8")); d = json.load(open(REF / f, encoding="utf-8"))
    assert dec(e["data"]) == d, f"decode mismatch {f}"
    assert dec(enc(d)) == d, f"re-encode mismatch {f}"
    assert e["format"] == FORMAT and e["version"] == VERSION and e["settingsCount"] == len(d), f
    pairs += 1
assert pairs > 0, "no reference pair to validate the codec against"
print(f"codec positive control: {pairs} reference pairs round-trip both directions")

flown = json.load(open(REF / "toggle-config_V293_r64_ARM-A_asflown.decoded.json", encoding="utf-8"))
assert flown["AccordDobHz"] == 0.6 and flown["AccordHoldLevel"] is True, "ARM-A is not the rev 6.4 as-flown config"
armd = dict(flown)
armd["AccordDobHz"] = 0.0
diff = {k: (flown.get(k), armd.get(k)) for k in set(flown) | set(armd) if flown.get(k) != armd.get(k)}
assert diff == {"AccordDobHz": (0.6, 0.0)}, diff

name = "toggle-config_V293_r64_ARM-D_observer-off"
out = REF / f"{name}.json"
json.dump({"format": FORMAT, "version": VERSION, "settingsCount": len(armd), "data": enc(armd)}, open(out, "w", encoding="utf-8"), indent=1)
json.dump(armd, open(REF / f"{name}.decoded.json", "w", encoding="utf-8"), indent=1)
assert dec(json.load(open(out, encoding="utf-8"))["data"]) == armd, "written file does not decode to the intended config"
print(f"wrote {out.name}: {len(armd)} settings, one change {diff}, verified by decoding the written file")
