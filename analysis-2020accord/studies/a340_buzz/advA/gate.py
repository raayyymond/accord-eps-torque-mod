import re,sys,glob
sys.path.insert(0,"builds/telemetry"); sys.path.insert(0,"lib")
from encode_eps import parse_x31
from pathlib import Path
FWR=Path("C:/Users/dudei/Desktop/Projects/accord-firmwares")
A=FWR/"analysis-2020accord"
for n in ["other bins/39990-TVA-A340.bin","_v300_a340_REV3_plain_image.bin","_v300_a340_REV4_plain_image.bin","_v37a_a340_REV4_plain_image.bin"]:
    b=(A/n).read_bytes(); print(n,b[0x13100:0x1310E], b[0x14120:0x14130])
srcs=["C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/flashing-2020accord/eps-update-tva.py","C:/Users/dudei/Downloads/eps-update-tva.py","C:/Users/dudei/Downloads/39990-TVA-A160 (Honda Accord)/Flashing script and instructions via ssh/eps-update-tva.py"]
rwds=sorted(glob.glob(str(FWR/"flashing-2020accord/rwd/*A340*")))
ecu=[b"39990-TVA-A340\0\0",b"39990-TVA,A340\0\0",b"39990-TVA,A34C\0\0",b"39990-TVA,A34D\0\0"]
for s in srcs:
    t=open(s,encoding="utf8").read()
    m=re.search(r"def app_id_matches_part.*?\n    return False\n",t,re.S)
    ns={"List":list}; exec("from typing import List\n"+m.group(0),ns); f=ns["app_id_matches_part"]
    print("FLASHER",s[-60:])
    for r in rwds:
        sup=[v for t_,vv in parse_x31(Path(r).read_bytes())["headers"] if t_==b"/" for v in vv]
        print("  ",Path(r).name[:34],[ (e[:14].decode(),f(e,sup)) for e in ecu])
