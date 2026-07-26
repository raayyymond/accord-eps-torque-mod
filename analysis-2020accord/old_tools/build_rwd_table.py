"""build_rwd_table.py — emit a markdown table of every iHDS .rwd:
filename | vehicle model & year | container (x5a/x31) | ISA (V850/SH-2A).

Joins per-file classification (classify_isa) with the code->model map in
rwd-xray/FILENAME_VEHICLE_REFERENCE.md. ISA is computed from each file's OWN
decoded bytes (see classify_isa)."""
import glob, os, re, gzip
from collections import Counter
import sys
ANALYSIS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ANALYSIS_DIR not in sys.path:
    sys.path.insert(0, ANALYSIS_DIR)
from firmware_paths import CALIB_FILES
import classify_isa as C

REF_MD = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'rwd-xray', 'FILENAME_VEHICLE_REFERENCE.md')
OUT    = 'IHDS_RWD_CLASSIFICATION.md'

# code -> "Model (years)"
ref={}
for line in open(REF_MD, encoding='utf-8'):
    m=re.match(r'^\|\s*([0-9A-Za-z]{3})\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|', line)
    if m:
        model=m.group(2).replace('<br>',' / ').strip()
        ref[m.group(1)]=(model, m.group(3).strip())

def code_of(name):
    base=name.split('.rwd')[0]
    m=re.search(r'[0-9A-Za-z]{5}[-_]?([0-9A-Za-z]{3})[-_]?[0-9A-Za-z]{4}', base)
    return m.group(1) if m else None

ISA_LABEL={'V850':'V850','SH2A':'SH-2A','undet':'undetermined','other-fmt':'—'}

files=sorted(str(p) for p in CALIB_FILES.glob('*.rwd*'))
rows=[]
for f in files:
    name=os.path.basename(f)
    try:
        cont,k,p=C.parse(C.load(f))
    except Exception:
        rows.append((name,'(parse error)','—','—')); continue
    if cont in ('x31','x5a'):
        isa=C.classify_file(k.hex() if k else '-', list(k), p)[0]
        cont_lbl=cont
    else:
        isa='other-fmt'; cont_lbl=cont          # 0x58/0x59/0x30 magic, not decoded
    code=code_of(name)
    model,yrs=ref.get(code,('(not in reference)',''))
    veh=f"{model} {yrs}".strip() if yrs else model
    rows.append((name, veh, cont_lbl, ISA_LABEL.get(isa,isa)))

cont_ct=Counter(r[2] for r in rows)
isa_ct =Counter(r[3] for r in rows)
with open(OUT,'w',encoding='utf-8') as o:
    o.write("# iHDS `.rwd` Classification Table\n\n")
    o.write("Per-file classification of every `.rwd` in the configured calibration directory.\n\n")
    o.write("- **Container**: `.rwd` header magic — `x31` (`31 0D 0A`) or `x5a` (`5A 0D 0A`); "
            "`other(0x..)` = a container format not decoded here.\n")
    o.write("- **ISA**: decided per file by decoding it and counting V850 `jr` (`0x8007`) vs "
            "SH-2A `sts.l pr` (`0x4F22`) in its own bytes. Neither the container nor the cipher "
            "key implies the ISA (e.g. cipher `010203` serves both). `undetermined` = too little "
            "code to call (often calibration-only payloads or a cipher we couldn't resolve).\n")
    o.write("- **Vehicle**: from `rwd-xray/FILENAME_VEHICLE_REFERENCE.md` (a subset — released "
            "firmware only), keyed on the 3-letter code in the filename.\n\n")
    o.write(f"**Totals:** {len(rows)} files — container "
            + ", ".join(f"{k}={v}" for k,v in sorted(cont_ct.items()))
            + "; ISA " + ", ".join(f"{k}={v}" for k,v in sorted(isa_ct.items())) + ".\n\n")
    o.write("| `.rwd` file | Vehicle (model / year) | Container | ISA |\n")
    o.write("|---|---|---|---|\n")
    for name,veh,cont,isa in rows:
        o.write(f"| `{name}` | {veh} | {cont} | {isa} |\n")
print(f"wrote {OUT}: {len(rows)} rows")
print("container:", dict(cont_ct))
print("ISA:", dict(isa_ct))
