"""build the kit v280-format cache + control-path cache for route 00000076--d0b7ea7e4d (V293 rev 5, 'T5').
Reuses v293_flight_read.extract / build_cs_cache unchanged (the decode every census uses).  Regenerable, gitignored
outputs: analysis-2020accord/_scratch/cache/v280/r76_v293r5*.{npz,json}, rlog-tools/studies/grind/_scratch/cs_r76_v293r5.npz."""
import os, sys, io, contextlib
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
KIT = r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod"
sys.path.insert(0, os.path.join(KIT, "rlog-tools", "studies", "grind"))
import v293_flight_read as FR
PFX = "75604b0a432fdc89_00000076--d0b7ea7e4d"
TAG = "r76_v293r5"
if not os.path.exists(os.path.join(FR.CACHE, TAG + ".npz")):
    FR.extract(PFX, TAG)
FR.build_cs_cache(TAG, prefix=PFX)
print("DONE")
