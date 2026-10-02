# -*- coding: utf-8 -*-
"""Write the V298 drive-1 Galaxy toggle config and its revert (delta files, Galaxy's own codec).

  toggle-config_V298_angle_loop.json                  = V295 r2's 26 keys + AccordEpsAngleLoop true + UseAutoSteerDelay true
  toggle-config_V298_angle_loop_REVERT_to_V295_r2.json = V295 r2's 26 keys + AccordEpsAngleLoop false + UseAutoSteerDelay true
(+ a .decoded.json beside each).  Every key is checked against the fork's params_keys.h at the working tree, the kit
codec is positive-controlled on the operator's 2026-09-10 backup, and both files are decoded back FROM DISK by the kit
codec and by the fork's own utilities.py functions (git show, never the working tree).  Files open with "x": never
overwrite.  Python = the kit's bin_decompile env, invoked as `python`.  Nothing is deployed; Galaxy restore is the
operator's action.
"""
import ast, base64, hashlib, importlib.util, json, os, re, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod"
FORK = r"C:/Users/dudei/Desktop/Projects/openpilots/raayyymond-StarPilot/StarPilot"
REF = os.path.join(KIT, "analysis-2020accord", "reference")
R2 = "toggle-config_V295_r2"
OUT = "toggle-config_V298_angle_loop"
REVERT = OUT + "_REVERT_to_V295_r2"

spec = importlib.util.spec_from_file_location("mgtc", os.path.join(KIT, "tools", "make_galaxy_toggle_config.py"))
K = importlib.util.module_from_spec(spec); spec.loader.exec_module(K)
K.positive_control()


def fork_codec(commit="20d24ab79"):
  src = subprocess.run(["git", "-C", FORK, "show", f"{commit}:starpilot/system/the_galaxy/utilities.py"],
                       capture_output=True, text=True, encoding="utf-8", check=True).stdout
  keep = [n for n in ast.parse(src).body if (isinstance(n, ast.FunctionDef) and n.name in
          {"xor_encrypt_decrypt", "encode_parameters", "decode_parameters"}) or
          (isinstance(n, ast.Assign) and any(getattr(t, "id", "") == "XOR_KEY" for t in n.targets))]
  ns = {"base64": base64, "json": json}
  exec(compile(ast.Module(body=keep, type_ignores=[]), "fork_utilities", "exec"), ns)
  assert ns["XOR_KEY"] == K.XOR_KEY
  return ns


F = fork_codec()
assert subprocess.run(["git", "-C", FORK, "diff", "--quiet", "20d24ab79", "--", "starpilot/system/the_galaxy/utilities.py"]).returncode == 0
fork_keys = set(re.findall(r'\{"(\w+)", \{', open(os.path.join(FORK, "common", "params_keys.h"), encoding="utf-8").read()))
assert "AccordEpsAngleLoop" in fork_keys, "the fork working tree does not declare AccordEpsAngleLoop"

r2_enc = json.load(open(os.path.join(REF, R2 + ".json"), encoding="utf-8"))
r2 = json.load(open(os.path.join(REF, R2 + ".decoded.json"), encoding="utf-8"))
assert K.decode_parameters(r2_enc["data"]) == r2 == F["decode_parameters"](r2_enc["data"]) and len(r2) == 26

configs = {
  OUT: dict(r2, AccordEpsAngleLoop=True, UseAutoSteerDelay=True),
  REVERT: dict(r2, AccordEpsAngleLoop=False, UseAutoSteerDelay=True),
}
for name, vals in configs.items():
  assert set(vals) <= fork_keys, set(vals) - fork_keys
  assert {k: v for k, v in vals.items() if k in r2 and v != r2[k]} == {}, "a V295 r2 value moved"
  wrapper = {"format": r2_enc["format"], "version": r2_enc["version"], "settingsCount": len(vals), "data": K.encode_parameters(vals)}
  assert F["encode_parameters"](vals) == wrapper["data"]
  p_enc, p_dec = os.path.join(HERE, name + ".json"), os.path.join(HERE, name + ".decoded.json")
  with open(p_enc, "x", encoding="utf-8") as fh:
    json.dump(wrapper, fh, indent=1)
  with open(p_dec, "x", encoding="utf-8") as fh:
    json.dump(vals, fh, indent=1)
  back = json.load(open(p_enc, encoding="utf-8"))
  assert K.decode_parameters(back["data"]) == vals == F["decode_parameters"](back["data"]) == json.load(open(p_dec, encoding="utf-8"))
  print("wrote %s.json (%d keys) sha256 %s; vs V295 r2: %s" % (name, len(vals), hashlib.sha256(open(p_enc, "rb").read()).hexdigest(),
        {k: (r2.get(k, "<absent>"), v) for k, v in vals.items() if r2.get(k, "<absent>") != v}))
