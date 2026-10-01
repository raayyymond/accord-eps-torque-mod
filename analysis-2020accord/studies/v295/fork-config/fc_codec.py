# -*- coding: utf-8 -*-
"""fc_codec: the two codecs for the Galaxy toggle files.
  * KIT:  tools/make_galaxy_toggle_config.py (imported, reused verbatim: xor_encrypt_decrypt / encode_parameters /
          decode_parameters / positive_control against the operator's 2026-09-10 backup).
  * FORK: the fork's OWN functions, extracted by AST from `git show 20d24ab79:starpilot/system/the_galaxy/utilities.py`
          (XOR_KEY, xor_encrypt_decrypt, encode_parameters, decode_parameters) and exec'd in an isolated namespace with
          only base64 + json -- the fork's working tree is never read or written (git show reads the object store).
"""
import ast
import base64
import importlib.util
import json
import os
import subprocess

KIT = r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod"
FORK = r"C:/Users/dudei/Desktop/Projects/openpilots/raayyymond-StarPilot/StarPilot"
FORK_COMMIT = "20d24ab79"
REF = os.path.join(KIT, "analysis-2020accord", "reference")


def kit_codec():
    spec = importlib.util.spec_from_file_location("mgtc", os.path.join(KIT, "tools", "make_galaxy_toggle_config.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def fork_codec():
    src = subprocess.run(["git", "-C", FORK, "show", "%s:starpilot/system/the_galaxy/utilities.py" % FORK_COMMIT],
                         capture_output=True, text=True, encoding="utf-8", check=True).stdout
    tree = ast.parse(src)
    want_f = {"xor_encrypt_decrypt", "encode_parameters", "decode_parameters"}
    keep = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name in want_f:
            keep.append(node)
        elif isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "XOR_KEY" for t in node.targets):
            keep.append(node)
    got = {n.name for n in keep if isinstance(n, ast.FunctionDef)}
    assert got == want_f, got
    mod = ast.Module(body=keep, type_ignores=[])
    ns = {"base64": base64, "json": json}
    exec(compile(mod, "fork_utilities_%s" % FORK_COMMIT, "exec"), ns)
    blob = hashlib_sha(src)
    return ns, blob


def hashlib_sha(s):
    import hashlib
    return hashlib.sha256(s.encode("utf-8")).hexdigest()
