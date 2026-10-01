# -*- coding: utf-8 -*-
"""f8: codec positive controls BEFORE any file is written.
  1. the kit codec's own positive control (the operator's 526-key 2026-09-10 backup round-trips).
  2. the FORK's decode_parameters (extracted from 20d24ab79) decodes every kit reference pair to its .decoded.json,
     incl. the flown r1 file; and fork encode == kit encode byte for byte on those dicts (same json.dumps, same key)."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fc_codec as C

K = C.kit_codec()
K.positive_control()
print("1. kit positive control: OK (operator's 2026-09-10 backup round-trips both ways)")
ns, sha = C.fork_codec()
print("   fork utilities.py @%s sha256 %s; XOR_KEY equal to kit's: %s" % (C.FORK_COMMIT, sha[:16], ns["XOR_KEY"] == K.XOR_KEY))
assert ns["XOR_KEY"] == K.XOR_KEY
n = 0
for f in sorted(os.listdir(C.REF)):
    if not f.endswith(".decoded.json"):
        continue
    ep = os.path.join(C.REF, f.replace(".decoded.json", ".json"))
    if not os.path.exists(ep):
        continue
    e = json.load(open(ep, encoding="utf-8"))
    d = json.load(open(os.path.join(C.REF, f), encoding="utf-8"))
    assert ns["decode_parameters"](e["data"]) == d, f
    assert ns["encode_parameters"](d) == K.encode_parameters(d), f
    n += 1
print("2. fork decode_parameters == .decoded.json on %d reference pairs (incl. the flown V294 r1); fork encode == kit encode" % n)
r1 = json.load(open(os.path.join(C.REF, "toggle-config_V294_accel-trim_r1.json"), encoding="utf-8"))
print("   r1 wrapper keys:", sorted(r1), " settingsCount", r1["settingsCount"])
