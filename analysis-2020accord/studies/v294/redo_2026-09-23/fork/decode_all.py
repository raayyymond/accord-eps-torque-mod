"""Decode every toggle config in the kit with the FORK's own codec functions (AST-extracted verbatim from
starpilot/system/the_galaxy/utilities.py at Dom HEAD), then simulate the fork's restore filter
(_get_toggle_backup_keys + _coerce_toggle_restore_value) against params_keys.h.
"""
import ast, base64, json, re, sys, subprocess
from pathlib import Path

FORK = Path(r"C:/Users/dudei/Desktop/Projects/openpilots/raayyymond-StarPilot/StarPilot")
KIT = Path(r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod")
REF = KIT / "analysis-2020accord" / "reference"
OUT = Path(__file__).resolve().parent

def git_show(rev, path):
    return subprocess.run(["git", "-C", str(FORK), "show", f"{rev}:{path}"], capture_output=True, text=True,
                          encoding="utf-8", check=True).stdout

# ---- 1. extract the fork's codec verbatim from HEAD (not the working tree) ----
src = git_show("54ff1ea39", "starpilot/system/the_galaxy/utilities.py")
tree = ast.parse(src)
ns = {"base64": base64, "json": json}
wanted = {"decode_parameters", "encode_parameters", "xor_encrypt_decrypt"}
got = set()
for node in tree.body:
    if isinstance(node, ast.FunctionDef) and node.name in wanted:
        exec(compile(ast.Module([node], []), "fork_utilities", "exec"), ns); got.add(node.name)
    if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == "XOR_KEY" for t in node.targets):
        exec(compile(ast.Module([node], []), "fork_utilities", "exec"), ns); got.add("XOR_KEY")
assert got == wanted | {"XOR_KEY"}, got
print("fork codec extracted:", sorted(got), "XOR_KEY =", repr(ns["XOR_KEY"]))
assert ns["XOR_KEY"] == "s8#pL3*Xj!aZ@dWq"
dec, enc = ns["decode_parameters"], ns["encode_parameters"]

# ---- 2. params_keys.h at HEAD: type, default, stock, flags ----
hdr = git_show("54ff1ea39", "common/params_keys.h")
PK = {}
for m in re.finditer(r'\{"(\w+)",\s*\{([^}]*)\}\}', hdr):
    parts = [p.strip() for p in m.group(2).split(",")]
    flags = parts[0]; typ = parts[1] if len(parts) > 1 else None
    dflt = parts[2].strip('"') if len(parts) > 2 else None
    stock = parts[3].strip('"') if len(parts) > 3 else None
    PK[m.group(1)] = dict(flags=flags, type=typ, default=dflt, stock=stock)
print("params_keys.h keys parsed:", len(PK))

def coerce(key, value):  # mirror of the_galaxy._coerce_toggle_restore_value for the types present here
    t = PK[key]["type"]
    if t == "BOOL":
        if isinstance(value, bool): return value
        if isinstance(value, (int, float)) and value in (0, 1): return bool(value)
        if isinstance(value, str):
            n = value.strip().lower()
            if n in {"1", "true", "yes", "on"}: return True
            if n in {"0", "false", "no", "off", ""}: return False
        raise ValueError(f"bool {key}")
    if t == "INT":
        if isinstance(value, bool): raise ValueError(f"int {key}")
        return int(float(value))
    if t == "FLOAT":
        if isinstance(value, bool): raise ValueError(f"float {key}")
        return float(value)
    raise ValueError(f"type {t} for {key}")

results = {}
files = sorted(p for p in REF.glob("*.json") if not p.name.endswith(".decoded.json"))
for p in files:
    wrap = json.load(open(p, encoding="utf-8"))
    if not isinstance(wrap, dict) or "data" not in wrap:
        continue
    d = dec(wrap["data"])
    assert enc(d) == wrap["data"], f"re-encode not byte-identical: {p.name}"
    dp = p.with_name(p.name[:-5] + ".decoded.json")
    readable = json.load(open(dp, encoding="utf-8")) if dp.exists() else None
    info = dict(format=wrap.get("format"), version=wrap.get("version"), settingsCount=wrap.get("settingsCount"),
                n=len(d), readable_match=(readable == d) if readable is not None else None,
                readable_types_match=(json.dumps(readable, sort_keys=True) == json.dumps(d, sort_keys=True)) if readable is not None else None)
    rest = {}
    for k, v in d.items():
        if k not in PK:
            rest[k] = "SKIP: not in params_keys.h"; continue
        if "PERSISTENT" not in PK[k]["flags"] or "DONT_LOG" in PK[k]["flags"]:
            rest[k] = "SKIP: flags"; continue
        try:
            rest[k] = coerce(k, v)
        except ValueError as e:
            rest[k] = f"SKIP: {e}"
    info["restore"] = rest
    info["values"] = d
    results[p.name] = info

json.dump(results, open(OUT / "decoded_all.json", "w"), indent=1, default=str)
for name, info in results.items():
    skips = {k: v for k, v in info["restore"].items() if isinstance(v, str) and v.startswith("SKIP")}
    print(f"{name:75s} fmt={info['format']} v={info['version']} count={info['settingsCount']}/{info['n']} "
          f"readable==decoded:{info['readable_match']} typed:{info['readable_types_match']} skips:{len(skips)}")
    if skips and "backup" not in name:
        print("   ", skips)
