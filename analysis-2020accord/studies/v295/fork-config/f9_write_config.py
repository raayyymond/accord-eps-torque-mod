# -*- coding: utf-8 -*-
"""f9: WRITE toggle-config_V295_r2 (+ .decoded.json) and toggle-config_V295_r2_REVERT_to_V294_r1 (+ .decoded.json).

r2 is a DELTA that carries EVERY key of the flown V294 r1 file (26 keys), with only the design's values changed, so the
file alone is a complete statement of the lateral state (same rule as r1).  The revert is r1's values exactly.
Wrapper = r1's own wrapper form (format / version / settingsCount / data, indent 1): the form the device restored and
flew on r71b (initData matched all 26 keys, V294-FLIGHT-ATTRIBUTION-r71b.md B).
Checks, in order, all asserted:
  1. kit codec positive control (operator's 2026-09-10 backup) + fork codec == kit codec on every reference pair (f8);
  2. decode(encode(x)) == x (kit) and fork decode_parameters(encoded) == x, for both files, IN MEMORY;
  3. the files are written with open(..., "x") (never overwrite), re-read FROM DISK, decoded by BOTH codecs == x;
  4. the r2 diff vs r1 is exactly CHANGES (no other key moved); the revert == r1 decoded, key for key.
Nothing is deployed.  Galaxy restore is the operator's action."""
import hashlib, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fc_codec as C

# ---------------------------------------------------------------------------------------------- THE DESIGN (edit here)
CHANGES = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "out",
                                   sys.argv[2] if len(sys.argv) > 2 else "r2_changes.json")))
# ------------------------------------------------------------------------------------------------------------------------

REF = C.REF
R1_NAME = "toggle-config_V294_accel-trim_r1"
STEM = sys.argv[1] if len(sys.argv) > 1 else "toggle-config_V295_r2"     # default: the gated deliverable
R2_NAME = STEM
RV_NAME = STEM + "_REVERT_to_V294_r1"

K = C.kit_codec()
K.positive_control()
ns, fsha = C.fork_codec()
fdec, fenc = ns["decode_parameters"], ns["encode_parameters"]
assert ns["XOR_KEY"] == K.XOR_KEY
r1_enc = json.load(open(os.path.join(REF, R1_NAME + ".json"), encoding="utf-8"))
r1 = json.load(open(os.path.join(REF, R1_NAME + ".decoded.json"), encoding="utf-8"))
assert fdec(r1_enc["data"]) == r1 == K.decode_parameters(r1_enc["data"])
assert set(CHANGES) <= set(r1), "a CHANGES key is not an r1 key: %s" % (set(CHANGES) - set(r1))
for k, v in CHANGES.items():
    assert type(v) is type(r1[k]), "type change on %s: %r -> %r" % (k, r1[k], v)

r2 = dict(r1)
r2.update(CHANGES)
diff = {k: (r1[k], r2[k]) for k in r1 if r1[k] != r2[k]}
assert set(diff) == {k for k in CHANGES if CHANGES[k] != r1[k]}
revert = dict(r1)


def wrap(values):
    return {"format": r1_enc["format"], "version": r1_enc["version"], "settingsCount": len(values),
            "data": K.encode_parameters(values)}


out = {}
for name, vals in ((R2_NAME, r2), (RV_NAME, revert)):
    w = wrap(vals)
    assert K.decode_parameters(w["data"]) == vals
    assert fdec(w["data"]) == vals
    assert fenc(vals) == w["data"]
    p_enc = os.path.join(REF, name + ".json")
    p_dec = os.path.join(REF, name + ".decoded.json")
    with open(p_enc, "x", encoding="utf-8") as fh:
        json.dump(w, fh, indent=1)
    with open(p_dec, "x", encoding="utf-8") as fh:
        json.dump(vals, fh, indent=1)
    back = json.load(open(p_enc, encoding="utf-8"))
    assert K.decode_parameters(back["data"]) == vals and fdec(back["data"]) == vals
    assert json.load(open(p_dec, encoding="utf-8")) == vals
    assert back["settingsCount"] == len(vals) == 26
    out[name] = dict(sha_json=hashlib.sha256(open(p_enc, "rb").read()).hexdigest(),
                     sha_decoded=hashlib.sha256(open(p_dec, "rb").read()).hexdigest(), keys=len(vals))
assert json.load(open(os.path.join(REF, RV_NAME + ".decoded.json"), encoding="utf-8")) == r1
print("codec: kit positive control OK; fork utilities.py @%s sha %s: decode == kit on both files, from disk" % (C.FORK_COMMIT, fsha[:16]))
print("r2 vs r1 (the whole delta):", diff)
for k, v in out.items():
    print("wrote %s.json  sha256 %s  (%d keys); .decoded.json sha256 %s" % (k, v["sha_json"], v["keys"], v["sha_decoded"]))
json.dump(dict(diff=diff, files=out, fork_utilities_sha=fsha), open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                                              "out", "f9_write_out_%s.json" % STEM), "w"), indent=1)
