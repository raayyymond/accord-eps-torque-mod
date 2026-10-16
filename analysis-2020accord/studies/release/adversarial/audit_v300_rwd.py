import sys, glob, hashlib, importlib.util, os
os.environ["ACCORD_FIRMWARE_ROOT"]="C:/Users/dudei/Desktop/Projects/accord-firmwares"
K="C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/"
sys.path[:0]=[K+"flashing-2020accord",K+"analysis-2020accord/lib",K+"analysis-2020accord/builds",K+"analysis-2020accord/builds/telemetry",K+"analysis-2020accord/builds/v50_v79",K+"analysis-2020accord/builds/v108_plus",K+"analysis-2020accord/verify"]
import encode_eps as EE
R="C:/Users/dudei/Desktop/Projects/accord-firmwares/"
A=R+"analysis-2020accord/"
st=open(A+"stock_fw_dump/code.bin","rb").read()
v9=open(glob.glob(A+"_v299_*A16B_plain_image.bin")[0],"rb").read()
v0=open(glob.glob(A+"_v300_*plain_image.bin")[0],"rb").read()
rw0=open(glob.glob(R+"flashing-2020accord/rwd/*V300*.rwd")[0],"rb").read()
rw9=open(glob.glob(R+"flashing-2020accord/rwd/*V299*.rwd")[0],"rb").read()
print("rwd sha v300",hashlib.sha256(rw0).hexdigest()[:16],"v299",hashlib.sha256(rw9).hexdigest()[:16])
# decode table: independent derivation from the v38 pair (template rwd + plain image), not from the build script's keys
import build_vfourframe_tva as FF
from pathlib import Path
from firmware_paths import plain_image_path
v38_rwd=Path(FF.V38_RWD).read_bytes(); v38_plain=Path(plain_image_path(FF.V38_PLAIN)).read_bytes()
S,E=0x13000,0x100000
pi=EE.parse_x31(v38_rwd); enc=bytes(pi["encs"][0]); plain=v38_plain[S:E]
print("v38 enc len",len(enc),"plain len",len(plain))
tbl={}; ok=True
for e,p in zip(enc,plain):
    if tbl.setdefault(e,p)!=p: ok=False
print("cipher is a consistent byte->byte map from V38 pair:",ok,"entries",len(tbl))
# check decode table covers (bijection?) and decode both rwds with the empirical table
inv_ok=len(set(tbl.values()))==len(tbl); print("injective on observed",inv_ok)
for nm,rw,img in(("v300",rw0,v0),("v299",rw9,v9)):
    inf=EE.parse_x31(rw); e=bytes(inf["encs"][0])
    miss=[b for b in set(e) if b not in tbl]
    dec=bytes(tbl.get(b,0) for b in e)
    print(nm,"enc len",len(e),"nblocks",len(inf["encs"]),"unseen cipher bytes",len(miss),"payload==image[0x13000:0x100000]:",dec==img[S:E] if not miss else "n/a")
    print("  checksum ok:", end=" ")
    try: FF.assert_x31_checksum(rw,nm); print("yes")
    except Exception as ex: print("NO",ex)
    for t,vv in inf["headers"]: print("  hdr",t,[v.decode('latin1') for v in vv])
    print("  blocks meta:",inf["blocks"])
# flasher acceptance
spec=importlib.util.spec_from_file_location("epsup",K+"flashing-2020accord/eps-update-tva.py")
try:
    m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    sup=m.get_x31_supported_parts(EE.parse_x31(rw0)); print("supported:",sup)
    for a in(b"39990-TVA,A16B\x00\x00",b"39990-TVA,A16A\x00\x00",b"39990-TVA,A16C\x00\x00",b"39990-TVA-A160\x00\x00",b"39990-TVA-A110",b"39990-TVA,A16D\x00\x00",b"39990-TVB,A16B",b"39990-TVA,A16B"[:11]):
        print(" ECU",a,"->",m.app_id_matches_part(a,sup))
    print("  CAN addr:",hex(m.get_can_address_x31(EE.parse_x31(rw0))))
except Exception as ex: print("flasher import failed",repr(ex))
